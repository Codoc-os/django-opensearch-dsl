from unittest.mock import patch

from celery import Celery
from django.apps import AppConfig, apps
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils.module_loading import import_string
from opensearchpy.connection.connections import connections

from django_dummy_app.models import Continent, Country
from django_opensearch_dsl.apps import DODConfig

app = Celery("project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


class BaseSignalProcessorTestCase:
    """Base test case for signal processors."""

    SIGNAL_PROCESSOR: str
    app_config: AppConfig

    @classmethod
    def setUpClass(cls):
        """Teardown default signal processor and setup SIGNAL_PROCESSOR."""
        super().setUpClass()
        cls.app_config = apps.get_app_config("django_opensearch_dsl")
        cls.app_config.signal_processor.teardown()
        cls.app_config.signal_processor = import_string(cls.SIGNAL_PROCESSOR)(connections)

    @classmethod
    def tearDownClass(cls):
        """Teardown SIGNAL_PROCESSOR signal processor and setup default one."""
        super().tearDownClass()
        cls.app_config.signal_processor.teardown()
        cls.app_config.signal_processor = DODConfig.signal_processor_class()(connections)


class RealTimeSignalProcessorTestCase(BaseSignalProcessorTestCase, TestCase):
    SIGNAL_PROCESSOR = "django_opensearch_dsl.signals.RealTimeSignalProcessor"

    def test_saving_model_instance_triggers_update(self):
        with patch("django_opensearch_dsl.documents.bulk") as mock:
            initial_name = "MyOwnContinent"
            new_name = "MyOwnPeacefulContinent"
            continent = Continent.objects.create(name=initial_name)
            create_action = {
                "_id": continent.pk,
                "_op_type": "index",
                "_source": {"countries": [], "id": continent.pk, "name": initial_name},
                "_index": "continent",
            }
            self.assertEqual(1, mock.call_count)
            self.assertEqual([create_action], list(mock.call_args_list[0][1]["actions"]))

            continent.name = new_name
            continent.save()
            update_action = {
                "_id": continent.pk,
                "_op_type": "index",
                "_source": {"countries": [], "id": continent.pk, "name": new_name},
                "_index": "continent",
            }
            self.assertEqual(2, mock.call_count)
            self.assertEqual([update_action], list(mock.call_args_list[1][1]["actions"]))

    def test_deleting_model_instance_triggers_unindex(self):
        with patch("django_opensearch_dsl.documents.bulk") as mock:
            continent = Continent.objects.create(name="MyOwnContinent")
            create_action = {
                "_id": continent.pk,
                "_op_type": "index",
                "_source": {
                    "countries": [],
                    "id": continent.pk,
                    "name": continent.name,
                },
                "_index": "continent",
            }
            self.assertEqual(mock.call_count, 1)
            self.assertEqual([create_action], list(mock.call_args_list[0][1]["actions"]))

            pk = continent.pk
            continent.delete()
            # Restore the pk since mock args are lazy and would return `None`
            # for processor using this instance itself, but not other
            # processors.
            continent.pk = pk
            delete_action = {
                "_id": continent.pk,
                "_op_type": "delete",
                "_index": "continent",
                "_source": None,
            }
            self.assertEqual(mock.call_count, 2)
            self.assertEqual([delete_action], list(mock.call_args_list[1][1]["actions"]))

    def test_creating_and_deleting_model_instance_triggers_related(self):
        with patch("django_opensearch_dsl.documents.bulk") as mock:
            continent = Continent.objects.create(name="MyOwnContinent")
            create_continent_action = {
                "_id": continent.pk,
                "_op_type": "index",
                "_source": {
                    "countries": [],
                    "id": continent.pk,
                    "name": continent.name,
                },
                "_index": "continent",
            }
            self.assertEqual(mock.call_count, 1)
            self.assertEqual([create_continent_action], list(mock.call_args_list[0][1]["actions"]))

            # Creating a country should index a new country and update the related continent
            country = Country.objects.create(name="MyOwnCountry", continent=continent, area=100, population=100)
            create_country_action = {
                "_id": country.pk,
                "_op_type": "index",
                "_source": {
                    "area": 100,
                    "continent": {"id": 1, "name": "MyOwnContinent"},
                    "event_count_func": 0,
                    "event_count_prop": 0,
                    "events_id": [],
                    "id": 1,
                    "name": "MyOwnCountry",
                    "population": 100,
                },
                "_index": "country",
            }
            self.assertEqual(mock.call_count, 3)
            self.assertEqual([create_country_action], list(mock.call_args_list[1][1]["actions"]))
            update_continent_action = {
                "_id": continent.pk,
                "_op_type": "index",
                "_source": {
                    "countries": [
                        {
                            "id": 1,
                            "name": "MyOwnCountry",
                            "area": 100,
                            "population": 100,
                        }
                    ],
                    "id": continent.pk,
                    "name": continent.name,
                },
                "_index": "continent",
            }
            self.assertEqual([update_continent_action], list(mock.call_args_list[2][1]["actions"]))

            # Deleting the country should delete the associated document and
            # update the related continent
            pk = country.pk
            country.delete()
            # Restore the pk since mock args are lazy and would return `None`
            # for processor using this instance itself, but not other
            # processors.
            country.pk = pk
            delete_action = {
                "_id": country.pk,
                "_op_type": "delete",
                "_index": "country",
                "_source": None,
            }
            self.assertGreaterEqual(mock.call_count, 5)
            self.assertEqual([delete_action], list(mock.call_args_list[3][1]["actions"]))
            update_continent_action = create_continent_action
            self.assertEqual([update_continent_action], list(mock.call_args_list[4][1]["actions"]))

    def test_updating_model_instance_does_nothing_if_autosync_disabled(self):
        with patch("django_opensearch_dsl.documents.bulk") as mock:
            with patch(
                "django_opensearch_dsl.apps.DODConfig.autosync_enabled",
                return_value=False,
            ):
                Continent.objects.create(name="MyOwnContinent")
                self.assertEqual(mock.call_count, 0)

    def test_updating_model_instance_does_nothing_if_document_ignores_signals(self):
        with patch("django_opensearch_dsl.documents.bulk") as mock:
            with patch(
                "django_dummy_app.documents.ContinentDocument.django.ignore_signals",
                return_value=True,
            ):
                Continent.objects.create(name="MyOwnContinent")
                self.assertEqual(mock.call_count, 0)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class CelerySignalProcessorTestCase(RealTimeSignalProcessorTestCase):
    SIGNAL_PROCESSOR = "django_opensearch_dsl.signals.CelerySignalProcessor"

    def test_saving_model_instance_triggers_update(self):
        with patch("django_opensearch_dsl.documents.bulk") as mock:
            initial_name = "MyOwnContinent"
            new_name = "MyOwnPeacefulContinent"
            with self.captureOnCommitCallbacks(execute=True):
                continent = Continent.objects.create(name=initial_name)
            create_action = {
                "_id": continent.pk,
                "_op_type": "index",
                "_source": {"countries": [], "id": continent.pk, "name": initial_name},
                "_index": "continent",
            }
            self.assertEqual(1, mock.call_count)
            self.assertEqual([create_action], list(mock.call_args_list[0][1]["actions"]))

            continent.name = new_name
            with self.captureOnCommitCallbacks(execute=True):
                continent.save()
            update_action = {
                "_id": continent.pk,
                "_op_type": "index",
                "_source": {"countries": [], "id": continent.pk, "name": new_name},
                "_index": "continent",
            }
            self.assertEqual(2, mock.call_count)
            self.assertEqual([update_action], list(mock.call_args_list[1][1]["actions"]))

    def test_deleting_model_instance_triggers_unindex(self):
        with patch("django_opensearch_dsl.documents.bulk") as mock:
            with self.captureOnCommitCallbacks(execute=True):
                continent = Continent.objects.create(name="MyOwnContinent")
            create_action = {
                "_id": continent.pk,
                "_op_type": "index",
                "_source": {
                    "countries": [],
                    "id": continent.pk,
                    "name": continent.name,
                },
                "_index": "continent",
            }
            self.assertEqual(mock.call_count, 1)
            self.assertEqual([create_action], list(mock.call_args_list[0][1]["actions"]))

            pk = continent.pk
            with self.captureOnCommitCallbacks(execute=True):
                continent.delete()
            # Restore the pk since mock args are lazy and would return `None`
            # for processor using this instance itself, but not other
            # processors.
            continent.pk = pk
            delete_action = {
                "_id": continent.pk,
                "_op_type": "delete",
                "_index": "continent",
                "_source": None,
            }
            self.assertEqual(mock.call_count, 2)
            self.assertEqual([delete_action], list(mock.call_args_list[1][1]["actions"]))

    def test_creating_and_deleting_model_instance_triggers_related(self):
        with patch("django_opensearch_dsl.documents.bulk") as mock:
            with self.captureOnCommitCallbacks(execute=True):
                continent = Continent.objects.create(name="MyOwnContinent")
            create_continent_action = {
                "_id": continent.pk,
                "_op_type": "index",
                "_source": {
                    "countries": [],
                    "id": continent.pk,
                    "name": continent.name,
                },
                "_index": "continent",
            }
            self.assertEqual(mock.call_count, 1)
            self.assertEqual([create_continent_action], list(mock.call_args_list[0][1]["actions"]))
            with self.captureOnCommitCallbacks(execute=True):
                # Creating a country should index a new country and update the related continent
                country = Country.objects.create(name="MyOwnCountry", continent=continent, area=100, population=100)
            create_country_action = {
                "_id": country.pk,
                "_op_type": "index",
                "_source": {
                    "area": 100,
                    "continent": {"id": 1, "name": "MyOwnContinent"},
                    "event_count_func": 0,
                    "event_count_prop": 0,
                    "events_id": [],
                    "id": 1,
                    "name": "MyOwnCountry",
                    "population": 100,
                },
                "_index": "country",
            }
            self.assertEqual(mock.call_count, 3)
            self.assertEqual([create_country_action], list(mock.call_args_list[1][1]["actions"]))
            update_continent_action = {
                "_id": continent.pk,
                "_op_type": "index",
                "_source": {
                    "countries": [
                        {
                            "id": 1,
                            "name": "MyOwnCountry",
                            "area": 100,
                            "population": 100,
                        }
                    ],
                    "id": continent.pk,
                    "name": continent.name,
                },
                "_index": "continent",
            }
            self.assertEqual([update_continent_action], list(mock.call_args_list[2][1]["actions"]))

            # Deleting the country should delete the associated document and
            # update the related continent
            pk = country.pk
            with self.captureOnCommitCallbacks(execute=True):
                country.delete()
            # Restore the pk since mock args are lazy and would return `None`
            # for processor using this instance itself, but not other
            # processors.
            country.pk = pk
            delete_action = {
                "_id": country.pk,
                "_op_type": "delete",
                "_index": "country",
                "_source": None,
            }
            self.assertGreaterEqual(mock.call_count, 5)
            self.assertEqual([delete_action], list(mock.call_args_list[3][1]["actions"]))
            update_continent_action = create_continent_action
            self.assertEqual([update_continent_action], list(mock.call_args_list[4][1]["actions"]))
