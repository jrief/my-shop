# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cms.utils import get_current_site
from cms.utils.page import get_page_from_path
from django.core.urlresolvers import reverse
from filer.models.imagemodels import Image
from parler_rest.serializers import TranslatableModelSerializerMixin, TranslatedFieldsField, TranslatedField
from rest_framework import serializers
from myshop.models import (Commodity, SmartCard, SmartPhoneModel, SmartPhoneVariant, Manufacturer, OperatingSystem,
                           ProductPage, ProductImage)


class CMSPagesField(serializers.Field):
    def to_representation(self, value):
        urls = {page.get_absolute_url() for page in value.all()}
        return list(urls)

    def to_internal_value(self, data):
        site = get_current_site()
        pages_root = reverse('pages-root')
        ret = []
        for path in data:
            if path.startswith(pages_root):
                path = path[len(pages_root):]
            # strip any final slash
            if path.endswith('/'):
                path = path[:-1]
            page = get_page_from_path(site, path)
            if page:
                ret.append(page)
        return ret


class ImagesField(serializers.Field):
    def to_representation(self, value):
        return list(value.values_list('pk', flat=True))

    def to_internal_value(self, data):
        return list(Image.objects.filter(pk__in=data))


class ValueRelatedField(serializers.RelatedField):
    """
    A serializer field used to access a single value from a related model.
    Usage:

        myfield = ValueRelatedField(model=MyModel)
        myfield = ValueRelatedField(model=MyModel, field_name='myfield')

    This serializes objects of type ``MyModel`` so that that the return data is a simple scalar.

    On deserialization it creates an object of type ``MyModel``, if none could be found with the
    given field name.
    """
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model')
        self.related_field_name = kwargs.pop('field_name', 'name')
        super(ValueRelatedField, self).__init__(*args, **kwargs)

    def get_queryset(self):
        return self.model.objects.all()

    def to_representation(self, value):
        return getattr(value, self.related_field_name)

    def to_internal_value(self, value):
        data = {self.related_field_name: value}
        instance, _ = self.model.objects.get_or_create(**data)
        return instance


class ProductSerializer(serializers.ModelSerializer):
    product_model = serializers.CharField(read_only=True)
    manufacturer = ValueRelatedField(model=Manufacturer)
    caption = TranslatedField()
    cms_pages = CMSPagesField()
    images = ImagesField()

    class Meta:
        exclude = ['id', 'polymorphic_ctype', 'updated_at']

    def create(self, validated_data):
        cms_pages = validated_data.pop('cms_pages')
        images = validated_data.pop('images')
        product = super(ProductSerializer, self).create(validated_data)
        for page in cms_pages:
            ProductPage.objects.create(product=product, page=page)
        for image in images:
            ProductImage.objects.create(product=product, image=image)
        return product


class CommoditySerializer(TranslatableModelSerializerMixin, ProductSerializer):
    class Meta(ProductSerializer.Meta):
        model = Commodity
        exclude = ['id', 'placeholder', 'polymorphic_ctype', 'updated_at']


class SmartCardSerializer(TranslatableModelSerializerMixin, ProductSerializer):
    multilingual = TranslatedFieldsField()

    class Meta(ProductSerializer.Meta):
        model = SmartCard


class SmartphoneVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmartPhoneVariant
        fields = ['product_code', 'unit_price', 'storage']


class SmartPhoneModelSerializer(TranslatableModelSerializerMixin, ProductSerializer):
    multilingual = TranslatedFieldsField()
    operating_system = ValueRelatedField(model=OperatingSystem)
    variants = SmartphoneVariantSerializer(many=True)

    class Meta(ProductSerializer.Meta):
        model = SmartPhoneModel

    def create(self, validated_data):
        variants = validated_data.pop('variants')
        product = super(SmartPhoneModelSerializer, self).create(validated_data)
        for variant in variants:
            SmartPhoneVariant.objects.create(product=product, **variant)
        return product
