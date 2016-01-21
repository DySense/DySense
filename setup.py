from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

if __name__ == "__main__":
    setup(name='dysense',
          version='1.0',
          description='Dynamic Sensor Interface',
          long_description=readme(),
          keywords='data sensor htp phenotyping',
          url='TODO',
          author='',
          author_email='',
          license='TODO',
          packages=['source'],
          install_requires=[
              'pyserial',
			  'pyyaml',
			  'pyzmq',
			  'pyqt4'
          ],
          zip_safe=False)