{ pkgs ? import <nixpkgs> {}}:

pkgs.mkShell {
  buildInputs = with pkgs.python3Packages; [
    feedparser matrix-nio docopt aiohttp aiofiles
  ];
  nativeBuildInputs = with pkgs.python3Packages; [
    mypy
  ];
}
