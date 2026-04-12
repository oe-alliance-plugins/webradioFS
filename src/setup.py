from setuptools import setup
import setup_translate

pkg = 'Extensions.webradioFS'
setup(name='enigma2-plugin-extensions-webradiofs',
       version='3.0',
       description='webradioFS streaming search for Enigma2',
       package_dir={pkg: 'webradioFS'},
       packages=[pkg],
       package_data={pkg: ['data/*.png', 'skin/fHD/*.xml', 'skin/HD/*.xml', 'skin/images/*.png', 'skin/SD/*.xml', 'skin/XD/*.xml', 'skin/*.txt', 'skin/*.xml', 'skin/*.ttf', 'skin/images/*.ico', '*.png', '*.xml', 'locale/*/LC_MESSAGES/*.mo', '*.txt']},
       cmdclass=setup_translate.cmdclass,  # for translation
      )
