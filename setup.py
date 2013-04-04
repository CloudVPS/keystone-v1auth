#!/usr/bin/python
# Copyright 2012 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup

setup(name='keystone_v1auth',
      version='1.0.0',
      description='Keystone v1 auth compatibility',
      author='Koert van der Veer, CloudVPS',
      author_email='koert@cloudvps.com',
      url='https://github.com/CloudVPS/keystone_v1auth',
      packages=['keystone_v1auth'],
      requires=['keystone(>=2012.1.0)'],
      # entry_points={'paste.filter_factory':
      #                   ['swift3=swift3.middleware:filter_factory']}
)