from setuptools import setup, find_packages
import sys, os

version = '0.0'

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
          # -*- Extra requirements: -*-
      ],
      entry_points={
         'fanstatic.libraries': [
            'gatekeeper = gatekeeper.resources:library',
         ],
         'paste.app_factory': [
             'app = gatekeeper.utils:app',
         ],
         'paste.filter_factory': [
             'global_config = gatekeeper.utils:configuration',
         ],
      }
      )
