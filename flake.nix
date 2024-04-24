{
  description = ''
    Nix developpement shell for this project.

    This will give you a working python 3.11 for executing tests.

    This is not mandatory. it's just help for those using nix.
  '';

  inputs = { nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable"; };

  outputs = { self, nixpkgs }:
    let
      allSystems = [
        "x86_64-linux"
      ];

      forAllSystems = fn:
        nixpkgs.lib.genAttrs allSystems
          (system: fn { pkgs = import nixpkgs { inherit system; }; });
    in
    {
      devShells = forAllSystems ({ pkgs }: {
        default = pkgs.mkShell {
          name = "default";
          nativeBuildInputs = with pkgs; [
            watchexec
            just
            (python310.withPackages (p: with p; [
              ipython
              packaging
              pytest
              docker
              ansible
            ]))
          ];
        };
      });
    };
}

