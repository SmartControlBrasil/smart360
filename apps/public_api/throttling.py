from rest_framework.throttling import UserRateThrottle


class PublicApiBurstRateThrottle(UserRateThrottle):
    scope = "public_api_burst"


class PublicApiSustainedRateThrottle(UserRateThrottle):
    scope = "public_api_sustained"
