{
  description = "CCNA Study Network Automation Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        
        # Python environment with essential network automation libraries
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          # Essential libraries
          netmiko
          prettytable
          ansible-core # Ansible Python API
          pip          # Modern pip
        ]);

      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.uv            # Modern Python package manager
            pkgs.ansible       # Ansible CLI
            pkgs.sshpass       # For Ansible password auth if needed
          ];

          shellHook = ''
            echo "🚀 Network Automation Environment Loaded"
            echo "Python: $(python --version)"
            echo "Ansible: $(ansible --version | head -n1)"
            export PYTHONPATH=$PWD/lib:$PYTHONPATH
          '';
        };
      }
    );
}
