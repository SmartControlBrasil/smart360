from drf_spectacular.utils import OpenApiParameter, extend_schema

from shared_kernel.api_docs.responses import common_error_responses


COMMON_LIST_PARAMETERS = [
    OpenApiParameter(name="page", type=int, location=OpenApiParameter.QUERY, description="Numero da pagina."),
    OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, description="Busca textual."),
    OpenApiParameter(name="ordering", type=str, location=OpenApiParameter.QUERY, description="Campo de ordenacao."),
]


def list_endpoint_schema(*, summary, description, parameters=None, tags=None):
    return extend_schema(
        summary=summary,
        description=description,
        parameters=(parameters or []) + COMMON_LIST_PARAMETERS,
        tags=tags or [],
        responses=common_error_responses(),
    )


def action_endpoint_schema(*, summary, description, request=None, responses=None, tags=None, parameters=None, examples=None):
    base_responses = common_error_responses(include_not_found=True)
    if responses:
        base_responses.update(responses)
    return extend_schema(
        summary=summary,
        description=description,
        request=request,
        responses=base_responses,
        tags=tags or [],
        parameters=parameters or [],
        examples=examples or [],
    )

