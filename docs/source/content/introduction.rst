Introduction
=============

OpenEmailSequence is an open source Django app for building email drip sequences from
`Django's admin <https://docs.djangoproject.com/en/stable/ref/contrib/admin/>`_ and a
queryset over your user model. You write each email once, describe who should receive it
as a set of queryset rules, and a management command sends it at the right moment.

For example, you can send a follow-up to everyone who hasn't logged in for a day, or a
different email to everyone who registered more than a week ago, without writing code for
either — the targeting is defined in the admin.
