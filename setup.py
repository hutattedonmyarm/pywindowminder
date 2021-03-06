from setuptools import setup

setup(
   name='pywindowminder',
   version='0.1',
   description='Sends window opening reminders',
   author='phlaym',
   author_email='aymmor@icloud.com',
   packages=['pywindowminder'],
   install_requires=['wheel', 'aiohttp'], #external packages as dependencies
)