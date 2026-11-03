from rest_framework import generics
from rest_framework.views import APIView

from core.pagination import StandardPagination
from core.responses import success_response

from .serializers import ProductDetailSerializer, ProductListSerializer, ProductQuerySerializer
from .services import get_product_by_id, get_products


class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        params = ProductQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        return get_products(params.validated_data)


class ProductDetailView(APIView):
    def get(self, request, product_id):
        product = get_product_by_id(product_id)
        return success_response(ProductDetailSerializer(product).data)
