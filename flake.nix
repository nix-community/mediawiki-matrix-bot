{
  description = "mediawiki_matrix_bot flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, nixpkgs }: {

    packages.x86_64-linux.mediawiki_matrix_bot = nixpkgs.legacyPackages.x86_64-linux.callPackage ./default.nix {};

    packages.x86_64-linux.default = self.packages.x86_64-linux.mediawiki_matrix_bot;

  };
}
