from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='gatekeeper',
      version=version,
      description="",
      long_description=""" """,
      classifiers=[],
      keywords='',
      author='',
      author_email='',
      url='',
      license='',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "Barrel",
          "PyCrypto",
          "cromlech.browser",
          "cromlech.dawnlight",
          "cromlech.security",
          "cromlech.webob",
          "dolmen.forms.crud",
          "dolmen.message",
          "dolmen.sqlcontainer",
          "dolmen.template",
          "dolmen.view",
          "js.bootstrap",
          "setuptools",
          "uvclight[sql]",
          "wsgistate",
      ],
      entry_points={
         'paste.app_factory': [
             'keeper = gatekeeper.app:keeper',
             'timeout = gatekeeper.login:timeout',
             'login = gatekeeper.login:login',
             'admin = gatekeeper.admin:admin',
             'unauthorized = gatekeeper.login:unauthorized',
         ],
         'paste.filter_factory': [
             'global_config = gatekeeper.utils:configuration',
         ],
      }
      )
