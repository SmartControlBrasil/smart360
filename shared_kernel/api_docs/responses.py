from drf_spectacular.utils import OpenApiResponse

from shared_kernel.api_docs.examples import (
    FORBIDDEN_EXAMPLE,
    NOT_FOUND_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
)


def common_error_responses(include_not_found=False):
    responses = {
        400: OpenApiResponse(description="Erro de validacao.", examples=[VALIDATION_ERROR_EXAMPLE]),
        401: OpenApiResponse(description="Nao autenticado.", examples=[UNAUTHORIZED_EXAMPLE]),
        403: OpenApiResponse(description="Permissao negada.", examples=[FORBIDDEN_EXAMPLE]),
    }
    if include_not_found:
        responses[404] = OpenApiResponse(description="Recurso nao encontrado.", examples=[NOT_FOUND_EXAMPLE])
    return responses

