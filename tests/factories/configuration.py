import factory

from apps.configuration_center.models import FeatureFlag, SystemSetting


class SystemSettingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SystemSetting

    key = factory.Sequence(lambda n: f"module.setting_{n}")
    group_name = "general"
    module_name = "core_platform"
    description = factory.Faker("sentence")
    value_type = SystemSetting.ValueType.STRING
    value_string = "value"
    value_json = factory.LazyFunction(dict)
    default_value_json = factory.LazyFunction(dict)
    is_active = True
    is_sensitive = False


class FeatureFlagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FeatureFlag

    key = factory.Sequence(lambda n: f"feature.flag_{n}")
    module_name = "smart_system"
    description = factory.Faker("sentence")
    flag_type = FeatureFlag.FlagType.BOOLEAN
    is_enabled = True
    rollout_percentage = 0
    config_json = factory.LazyFunction(dict)
    is_active = True

