{ config, pkgs, ...}:

{
   home.username = "eric";
   home.homeDirectory = "/home/eric";
   home.stateVersion = "25.11";
   programs.home-manager.enable = true;

   programs.nix-index = {
     enable = true;
     enableBashIntegration = true;
   };

   programs.bash = {
     enable = true;
     initExtra = ''
       if [ -f ~/.bash_common ]; then . ~/.bash_common; fi
     '';
   };
}
