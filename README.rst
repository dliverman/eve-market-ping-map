EVE Market Data Relay Ping Map (EMDRPM)
=======================================

:Author: Dylan Liverman

This application consists of a WebGL-based map of EVE that lights up when
market data arrives through EMDR. Each dot on the map represents a system,
and the brightness of each system shows how recently we saw data from it.

Each dot fades over about a minute.

`See it in action`_.

.. _See it in action: http://map.eve-emdr.com/

Powered by
----------

WebSockets, GoLang, and S3 for hosting of the static assets.

License
-------

The contents of this repository are licensed under the BSD License.
