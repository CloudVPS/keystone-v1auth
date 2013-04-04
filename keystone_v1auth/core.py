# Copyright (c) 2013 CloudVPS
#
# Documentation taken from swift tempauth, Copyright (c) 2011 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from keystone import catalog
from keystone import identity
from keystone import token
from keystone.common.wsgi import Application, Request

from webob import Response
from webob.exc import HTTPUnauthorized, HTTPBadRequest

import logging
import uuid

LOG = logging.getLogger(__name__)

class V1Auth(Application):

    def __init__(self, conf):
        self.catalog_api = catalog.Manager()
        self.identity_api = identity.Manager()
        self.token_api = token.Manager()

        super(V1Auth, self).__init__()

    def __call__(self, environment, start_response):
        req = Request(environment)
        response = self.handle(req)

        return response(environment, start_response)

    def handle(self, req):
        """
        Handles the various `request for token and service end point(s)` calls.
        There are various formats to support the various auth servers in the
        past. Examples::

            GET /v1/<act>/auth
                X-Auth-User: <act>:<usr>  or  X-Storage-User: <usr>
                X-Auth-Key: <key>         or  X-Storage-Pass: <key>
            GET <auth-prefix>/auth
                X-Auth-User: <act>:<usr>  or  X-Storage-User: <act>:<usr>
                X-Auth-Key: <key>         or  X-Storage-Pass: <key>
            GET <auth-prefix>/v1.0
                X-Auth-User: <act>:<usr>  or  X-Storage-User: <act>:<usr>
                X-Auth-Key: <key>         or  X-Storage-Pass: <key>

        On successful authentication, the response will have X-Auth-Token and
        X-Storage-Token set to the token to use with Swift and X-Storage-URL
        set to the URL to the default Swift cluster to use.

        :param req: The webob.Request to process.
        :returns: webob.Response, 2xx on success with data set as explained
                  above.
        """

        pathsegs = req.path[1:].split('/',2)

        if len(pathsegs) == 3 and pathsegs[0] == 'v1' and pathsegs[2] == 'auth':
            # GET <auth-prefix>/v1/<act>/auth
            #     X-Auth-User: <act>:<usr>  or  X-Storage-User: <usr>
            #     X-Auth-Key: <key>         or  X-Storage-Pass: <key>

            tenant_id = pathsegs[1]

            username = req.headers.get('x-storage-user') or \
                       req.headers.get('x-auth-user')

            if username and ':' in username:
                tenant_id2, username = username.split(':', 1)
                if tenant_id != tenant_id2:
                    return HTTPUnauthorized(request=req)

            password = req.headers.get('x-storage-pass') or \
                       req.headers.get('x-auth-key')

        elif pathsegs[0] in ('auth', 'v1.0'):
            # GET <auth-prefix>/auth
            #     X-Auth-User: <act>:<usr>  or  X-Storage-User: <act>:<usr>
            #     X-Auth-Key: <key>         or  X-Storage-Pass: <key>
            # GET <auth-prefix>/v1.0
            #     X-Auth-User: <act>:<usr>  or  X-Storage-User: <act>:<usr>
            #     X-Auth-Key: <key>         or  X-Storage-Pass: <key>

            username = req.headers.get('x-auth-user') or \
                   req.headers.get('x-storage-user')

            tenant_id = None
            if username and ':' in username:
                tenant_id, username = username.split(':', 1)

            password = req.headers.get('x-auth-key') or \
                       req.headers.get('x-storage-pass')
        else:
            return HTTPBadRequest(request=req)

        if not username or not password:
            # can't complete authentication without username&password
            return HTTPUnauthorized(request=req)

        user_ref = self.identity_api.get_user_by_name(user_name=username)

        if not user_ref:
            return HTTPUnauthorized(request=req)

        user_id = user_ref['id']

        # Try to determine the proper tenant-id
        if not tenant_id:
            user_tenants = self.identity_api.get_tenants_for_user(user_id)

            # User has only one tenant, he probably meant that one
            if len(user_tenants) == 1:
                tenant_id = user_tenants[0]
            else:
                # if there were multiple tenants for this user, he probably
                # meant the one with swiftoperator access.
                for user_tenant_id in user_tenants:
                    roles = self.identity_api.get_roles_for_user_and_tenant(
                        user_id=user_id, tenant_id=user_tenant_id
                    )
                    if self.conf['swift_role'] in roles:
                        if tenant_id:
                            # User has multiple tenants, can't use tenant
                            # guessing
                            return HTTPUnauthorized(request=req)

                        tenant_id = user_tenant_id

            LOG.notice("Selected tenant %s for user %s", tenant_id, user_id)

        # validate the user's password
        try:
            user_ref, tenant_ref, metadata_ref = self.identity_api.authenticate(
                user_id, tenant_id, password)
        except AssertionError:
            return HTTPUnauthorized(request=req)

        # Create a token
        token_id = uuid.uuid4().hex
        self.token_api.create_token( token_id, dict(id=token_id,
                                                    user=user_ref,
                                                    tenant=tenant_ref,
                                                    metadata=metadata_ref))

        # Parse the catalog to find the storage_url
        catalog = self.catalog_api.get_catalog(
            user_id=user_ref['id'],
            tenant_id=tenant_ref['id'],
            metadata=metadata_ref)

        url_type = self.conf['url_type']
        service_type = self.conf['service_type']
        for region, services in catalog.iteritems():
            if service_type in services:
                storage_url = services[service_type][url_type]
                break

        # All done!
        return Response(
            request=req,
            headers={
                'x-auth-token': token,
                'x-storage-token': token,
                'x-storage-url': storage_url,
            })

def app_factory(global_conf, **local_conf):
    conf = {
        'url_type': 'publicURL',
        'service_type': 'object-store',
        'swift_role': 'swiftoperator'
    }

    conf.update(global_conf)
    conf.update(local_conf)

    return V1Auth(conf)
