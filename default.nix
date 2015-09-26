with import <nixpkgs> {};

stdenv.mkDerivation {
  name = "foo";

  src = null;

  buildInputs = [ zlib libxml2 libxslt ];
}
