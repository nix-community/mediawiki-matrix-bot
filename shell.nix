{ pkgs ? import <nixpkgs> {}}:

pkgs.mkShell {
  nativeBuildInputs = with pkgs.python3Packages; [  feedparser matrix-nio docopt aiohttp aiofiles];
}
