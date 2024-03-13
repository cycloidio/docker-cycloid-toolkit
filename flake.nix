{
  description = "nix devshell example";

  inputs = { nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable"; };

  outputs = { self, nixpkgs }:
    let
      allSystems = [
        "x86_64-linux" # 64bit AMD/Intel x86
      ];

      forAllSystems = fn:
        nixpkgs.lib.genAttrs allSystems
        (system: fn { pkgs = import nixpkgs { inherit system; }; });
    in {
      # nix develop <flake-ref>#<name>
      # -- 
      # $ nix develop <flake-ref>#first
      devShells = forAllSystems ({ pkgs }: {
        default = pkgs.mkShell {
          name = "default";
          nativeBuildInputs = with pkgs; [
            (python311.withPackages (p: with p; [
              ipython
              packaging
              pytest
              ruff
              docker
              ansible
            ]))
          ];
        };
      });
    };
}

