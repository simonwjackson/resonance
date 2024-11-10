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
in
  pkgs.stdenv.mkDerivation {
    name = "resonance";
    src = ./.;

    buildInputs = [
      python-env
    ];

    nativeBuildInputs = [
      pkgs.makeWrapper
    ];

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
        --prefix PATH : ${pkgs.lib.makeBinPath [
        pkgs.jq
        pkgs.yt-dlp
        deadwax
        musicull
      ]}
    '';

    dontBuild = true;
  }
