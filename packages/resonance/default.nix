{
  inputs,
  pkgs,
  system,
  ...
}: let
  inherit (inputs.self.packages.${system}) deadwax musicull;

  python-packages = ps:
    with ps; [
      flask
      requests
      flask-caching
      typing-extensions
    ];
  python-env = pkgs.python3.withPackages python-packages;

  # Define runtime dependencies for the application
  runtimeDeps = [
    pkgs.jq
    pkgs.yt-dlp
    deadwax
    musicull
  ];

  # Define additional development-only dependencies
  devDeps = [
    pkgs.entr
  ];
in
  pkgs.stdenv.mkDerivation {
    name = "resonance";
    src = ./.;

    buildInputs =
      [
        python-env
      ]
      ++ runtimeDeps
      ++ devDeps;

    nativeBuildInputs = [
      pkgs.makeWrapper
    ];

    shellHook = ''
      export PYTHONPATH=$PWD:$PYTHONPATH
      export FLASK_APP=app.py
      export FLASK_ENV=development
      export PATH=${pkgs.lib.makeBinPath (runtimeDeps ++ devDeps)}:$PATH
    '';

    installPhase = ''
      mkdir -p $out/bin $out/lib/resonance

      # Copy all Python files and templates
      cp -r app.py routes templates static $out/lib/resonance/

      # Create a wrapper script
      cat > $out/bin/resonance << EOF
      #!${pkgs.bash}/bin/bash
      export PYTHONPATH=$out/lib/resonance:$PYTHONPATH
      export FLASK_APP=app.py
      export FLASK_ENV=production
      cd $out/lib/resonance
      exec ${python-env}/bin/python app.py "\$@"
      EOF
      chmod +x $out/bin/resonance

      wrapProgram $out/bin/resonance \
        --prefix PATH : ${pkgs.lib.makeBinPath runtimeDeps}  # Note: devDeps not included here
    '';

    dontBuild = true;
  }
