{ pkgs ? import <nixpkgs> {}}:

pkgs.python3Packages.buildPythonApplication {
  pname = "mediawiki-matrix-bot";
  version = "1.1.0";
  src = ./.;
  propagatedBuildInputs = with pkgs.python3Packages; [
    feedparser matrix-nio docopt aiohttp aiofiles
  ];
  nativeBuildInputs = with pkgs.python3Packages; [
    mypy
  ];
  checkPhase = ''
    mypy --strict mediawiki_matrix_bot
  '';
}
