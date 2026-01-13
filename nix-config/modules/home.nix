{ config, pkgs, ...}:

let username = "eric";
  in
{
  home.username = username;
  home.homeDirectory = "/home/${username}";
  home.stateVersion = "25.11";
  programs.home-manager.enable = true;

  home.packages = with pkgs; [
    # Python environment
    (python3.withPackages ( py: with py; [
      ipdb
      ipython
      matplotlib
      numpy
      pandas
      psutil
      scipy
    ]))

    # For wgpu programs in Rust
    libx11
    libxcursor
    libxi
    libxkbcommon
    # libGL
    # wgpu-utils
    vulkan-loader
  ];

  # Available programs defined in
  # https://github.com/nix-community/home-manager/tree/master/modules/programs

  programs.bash = {
    enable = true;

    sessionVariables = {
      # Provide the per-user library as a search path for any compiled
      # executables.  This doesn't follow the nix convention of
      # explicitly pinned libraries, but for now I'd rather have a
      # development environment
      LDFLAGS = "-Wl,-rpath,/etc/profiles/per-user/${username}/lib";
      RUSTFLAGS = "-C link-arg=-Wl,-rpath,/etc/profiles/per-user/${username}/lib";
    };
    initExtra = ''
       # Load sessionVariables.  Without this line, changes to
       # `sessionVariables` are only seen on the next login.
       if [ -f ~/.profile ]; then . ~/.profile; fi

       # Load standard configurations that are used on Nix and non-Nix platforms
       if [ -f ~/.bash_common ]; then . ~/.bash_common; fi
     '';
  };
}
