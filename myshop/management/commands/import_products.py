# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string
from django.utils.translation import activate


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('filename')

    def handle(self, verbosity, filename, *args, **options):
        activate(settings.LANGUAGE_CODE)
        with open(filename, 'r') as fh:
            data = json.load(fh)

        for product in data:
            product_model = product.pop('product_model')
            ProductModel = ContentType.objects.get(app_label='myshop', model=product_model)
            class_name = 'myshop.management.serializers.' + ProductModel.model_class().__name__ + 'Serializer'
            serializer_class = import_string(class_name)
            serializer = serializer_class(data=product)
            assert serializer.is_valid(), serializer.errors
            serializer.save()
        self.stdout.write("Imported ....")
