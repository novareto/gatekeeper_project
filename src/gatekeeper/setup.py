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
          "cromlech.webob",
          "cromlech.browser",
          "cromlech.dawnlight",
          "dolmen.template",
          "dolmen.view",
      ],
      entry_points={
         'fanstatic.libraries': [
            'gatekeeper = gatekeeper.resources:library',
         ],
         'paste.app_factory': [
             'keeper = gatekeeper.utils:keeper',
             'timeout = gatekeeper.login:timeout',
             'login = gatekeeper.login:Login',
             'unauthorized = gatekeeper.login:unauthorized',
         ],
         'paste.filter_factory': [
             'global_config = gatekeeper.utils:configuration',
         ],
      }
      )
