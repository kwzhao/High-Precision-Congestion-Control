export CC=gcc-9
export CXX=g++-9
CXXFLAGS=-w ./ns3 configure --build-profile=optimized --enable-examples --disable-tests --enable-python-bindings --disable-werror --disable-warnings
