from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 1000  # Set your maximum page size here

    def get_page_size(self, request):
        """
        Override the page size dynamically based on client input.
        """
        page_size = request.query_params.get(self.page_size_query_param)
        if page_size == 'all':
            return None  # Return None to indicate retrieving all values
        if page_size:
            try:
                return int(page_size)
            except ValueError:
                pass
        return self.page_size

    def paginate_queryset(self, queryset, request, view=None):
        """
        Override the pagination behavior to retrieve all values if 'all' parameter is provided.
        """
        page_size = self.get_page_size(request)
        if page_size is None:
            return None  # Return None to indicate retrieving all values
        return super().paginate_queryset(queryset, request, view)


class MessagePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_page_size(self, request):
        """
        Override the page size dynamically based on client input.
        """
        page_size = request.query_params.get(self.page_size_query_param)
        if page_size == 'all':
            return None  # Return None to indicate retrieving all values
        if page_size:
            try:
                return int(page_size)
            except ValueError:
                pass
        return self.page_size

    def paginate_queryset(self, queryset, request, view=None):
        """
        Override the pagination behavior to retrieve all values if 'all' parameter is provided.
        """
        page_size = self.get_page_size(request)
        if page_size is None:
            return None  # Return None to indicate retrieving all values
        return super().paginate_queryset(queryset, request, view)
