from setuptools import setup

setup(name='pyHS100',
      version='0.3.5.2',
      description='Interface for TPLink HS1xx plugs, HS2xx wall switches & LB1xx bulbs',
      url='https://github.com/GadgetReactor/pyHS100',
      author='Sean Seah (GadgetReactor)',
      author_email='sean@gadgetreactor.com',
      license='GPLv3',
      packages=['pyHS100'],
      install_requires=['click', 'click-datetime'],
      python_requires='>=3.4',
      entry_points={
            'console_scripts': [
                  'pyhs100=pyHS100.cli:cli',
            ],
      },
      zip_safe=False)
