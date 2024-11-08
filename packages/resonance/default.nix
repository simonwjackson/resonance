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
      mkdir -p $out/bin
      cp -r . $out/

      # Create a wrapper script
      cat > $out/bin/resonance << EOF
      #!${pkgs.bash}/bin/bash
      export PYTHONPATH=$out:$PYTHONPATH
      export FLASK_APP=app.py
      export FLASK_ENV=production
      exec ${python-env}/bin/python $out/app.py "\$@"
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
