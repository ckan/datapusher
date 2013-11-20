from setuptools import setup, find_packages

version = '1.0'

setup(name='datapusher',
      version=version,
      description="Service that allows automatic import of data to the CKAN DataStore.",
      long_description="""\
""",
      classifiers=[],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Dominik Moritz',
      author_email='dominik.moritz@okfn.org',
      url='',
      license='AGPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=['ckanserviceprovider',
                        'messytables>=0.12.0',
                        'python-slugify',
                        'Requests'],
      dependency_links=[
          'https://github.com/okfn/ckan-service-provider/tarball/master#egg=ckanserviceprovider',
      ],
      entry_points={
            'console_scripts': [
                  'datapusher = datapusher.main:main'
            ],
      },
)
