((magit-log:magit-log-mode "-n256" "--topo-order" "--graph" "--color" "--decorate")
 (magit-rebase "--autostash" "--interactive" "--rebase-merges=rebase-cousins"))
