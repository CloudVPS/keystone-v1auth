Keystone V1 authentication layer
================================

Compatibility layer for keystone. Intended for Cloudfile clients which haven't
implemented support for the newer v2.0 keystone authentication.

Installing
----------

Add the `v1auth` app to `/etc/keystone/keystone.conf`.

	[app:v1auth]
	paste.app_factory = keystone_v1auth:app_factory
    # url_type = publicURL
    # service_type = object-store
    # swift_role = swiftoperator

And add the `v1auth` routes to the main router in `/etc/keystone/keystone.conf`

	[composite:main]
	use = egg:Paste#urlmap
	/v2.0 = public_api
	/v1.0 = v1auth
	/auth = v1auth
	/ = public_version_api

