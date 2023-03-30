from django.test import TestCase
from opensearch_dsl import Q
from opensearch_dsl.connections import get_connection

from django_dummy_app.documents import CountryDocument, ContinentDocument
from django_dummy_app.models import Country, Continent


class DocumentTestCase(TestCase):
    fixtures = ["tests/django_dummy_app/geography_data.json"]

    def setUp(self) -> None:
        get_connection().indices.delete("_all")

    def test_search_country(self):
        CountryDocument.init()

        CountryDocument().update(CountryDocument().get_indexing_queryset(), "index", refresh=True)
        self.assertEqual(
            set(CountryDocument.search().query("term", **{"continent.name": "Europe"}).extra(size=300).to_queryset()),
            set(Country.objects.filter(continent__name="Europe")),
        )

    def test_search_country_cache(self):
        CountryDocument.init()

        CountryDocument().update(CountryDocument().get_indexing_queryset(), "index", refresh=True)
        search = CountryDocument.search().query("term", **{"continent.name": "Europe"}).extra(size=300)
        search.execute()
        self.assertEqual(
            set(search.to_queryset(keep_order=True)), set(Country.objects.filter(continent__name="Europe"))
        )

    def test_search_country_keep_order(self):
        CountryDocument.init()

        CountryDocument().update(CountryDocument().get_indexing_queryset(), "index", refresh=True)
        search = CountryDocument.search().query("term", **{"continent.name": "Europe"}).extra(size=300)
        self.assertEqual(
            set(search.to_queryset(keep_order=True)), set(Country.objects.filter(continent__name="Europe"))
        )

    def test_search_country_refresh_default_to_document(self):
        CountryDocument.init()

        CountryDocument().update(CountryDocument().get_indexing_queryset(), "index", refresh=True)
        self.assertEqual(
            set(CountryDocument.search().query("term", **{"continent.name": "Europe"}).extra(size=300).to_queryset()),
            set(Country.objects.filter(continent__name="Europe")),
        )

    def test_search_country_refresh_default_to_settings(self):
        ContinentDocument.init()

        ContinentDocument().update(ContinentDocument().get_indexing_queryset(), "index", refresh=True)
        search = ContinentDocument.search().query(
            "nested", path="countries", query=Q("term", **{"countries.name": "France"})
        )
        self.assertEqual(set(search.to_queryset()), set(Continent.objects.filter(countries__name="France")))

    def test_update_instance(self):
        ContinentDocument.init()

        ContinentDocument().update(Continent.objects.get(countries__name="France"), "index", refresh=True)
        search = ContinentDocument.search().query(
            "nested", path="countries", query=Q("term", **{"countries.name": "France"})
        )
        self.assertEqual(set(search.to_queryset()), set(Continent.objects.filter(countries__name="France")))
