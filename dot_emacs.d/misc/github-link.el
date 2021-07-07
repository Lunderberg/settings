;; Usage:
;; (autoload 'github-link "github-link" "Github Link" t)
;; (global-set-key (kbd "C-c g") 'github-link)

(defconst github-link-version "0.1"
  "github-link version.")

(defgroup github-link nil
  "Utility for generating links to public-facing github code."
  :prefix "github-link-"
  :link '(url-link :tag "Repository" "https://github.com/Lunderberg/settings/tree/master/dot_emacs.d/misc/github-link.el"))

(defcustom github-link-remotes '("upstream" "origin")
  "Git remote aliases to github repos.  These are checked in
   order to see if the upstream contains the pointed-to code to
   generate a link.  Any remotes not in this list are checked in
   alphabetical order after the remotes in this list."
  :type 'list
  :group 'github-link)

(defcustom github-link-branches '("main" "master")
  "Git branch names, in order of preference for where the link
   should be made to.  If a branch name exists, is in this list,
   and the branch has no differences to the selected lines
   relative to the current branch, then the link generated will
   point to that branch.  Otherwise, it will point to the current
   branch.

   This is intended to avoid creating links into development
   branches for code that hasn't been changed in that development
   branch."
  :type 'list
  :group 'github-link)

(defcustom github-link-context-lines 0
  "Number of lines of context used when checking a diff.  This is
   used when checking if a link can be made to upstream/main
   instead of the current branch.  The linked region must be at
   least this many lines away from the nearest changed line in
   order to generate a link to the main branch."
  :type 'int
  :group 'github-link)

(defun github-link-call-git (&rest args)
  (with-output-to-string
    (with-current-buffer standard-output
      (apply 'call-process "git" nil t nil args))))


(defclass github-link-git-branch ()
  ((name
    :initarg :name
    :initform ""
    :type string
    :documentation "The name of the branch.")
   (commit
    :initarg :commit
    :initform ""
    :type string
    :documentation "The short commit ID pointed to by the branch.")
   (remote-full
    :initarg :remote-full
    :initform nil
    :type string-or-null
    :documentation "The full name of the remote, if any.  For remote branches, this is equal to :name.")
   (remote-name
    :initarg :remote-name
    :initform nil
    :type string-or-null
    :documentation "The name of the remote, if any.")
   (remote-branch
    :initarg :remote-branch
    :initform nil
    :type string-or-null
    :documentation "The name of the tracking branch in the remote, if any.")
   (remote-username
    :initarg :remote-username
    :initform nil
    :type string-or-null
    :documentation "The Github username that ownes the repo that contains the remote tracking branch, if any.")
   (remote-repo-name
    :initarg :remote-repo-name
    :initform nil
    :type string-or-null
    :documentation "The Github name of the repo that contains the remote tracking, if any.")
   (is-active
    :initarg :is-active
    :initform nil
    :type boolean
    :documentation "If the branch specified is the currently active branch.")
   )
  :group github-link)

(cl-defmethod priority ((branch github-link-git-branch))
  (let* ((name (oref branch name))
         (split-name (split-string name "/"))
         (remote-name (nth 0 split-name))
         (remote-branch (nth 1 split-name))
         (remote-name-index (cl-position remote-name github-link-remotes :test 'equal))
         (remote-branch-index (cl-position remote-branch github-link-branches :test 'equal))
         )

    (cond
     ;; Remote branches come first, in order of github-link-remotes,
     ;; then branches.
     ((and remote-name-index remote-branch-index)
           (+ (* remote-name-index (seq-length github-link-branches))
              remote-branch-index))

     ;; Next comes the active branch, if it is tracking a remote
     ;; branch.
     ((and (oref branch is-active) (oref branch remote-full))
       (* (seq-length github-link-branches)
          (seq-length github-link-remotes)))

     ;; Anything else, we can't use, so it gets nil priority
     nil
     )
    )
  )

(defun all-diff-chunk-headers (string)
  (let ((regex (concat "@@ -"                 ;; Opening of diff chunk header
                        "\\([0-9]+\\)"         ;; Starting line of chunk in HEAD (group 1)
                        "\\(,\\([0-9]+\\)\\)?" ;; Length of chunk in HEAD (group 3)
                        " \\+"
                        "\\([0-9]+\\)"         ;; Starting line of chunk in branch (group 4)
                        "\\(,\\([0-9]+\\)\\)?" ;; Length of chunk in branch (group 6)
                        " @@"                  ;; Close of header
                        ))
        (pos 0)
        (matches nil))
    (save-match-data
      (let ((pos 0)
            (matches nil))
        (while (string-match regex string pos)
          (let* ((head-first (string-to-number (match-string 1 string)))
                 (head-length (string-to-number (or (match-string 3 string) "0")))
                 (head-last (+ head-first head-length))
                 (branch-first (string-to-number (match-string 4 string)))
                 (branch-length (string-to-number (or (match-string 6 string) "0")))
                 (branch-last (+ branch-first branch-length)))

            (push (list 'head-first head-first
                        'head-length head-length
                        'head-last head-last
                        'branch-first branch-first
                        'branch-length branch-length
                        'branch-last branch-last)
                  matches)
          (setq pos (match-end 0))))
        matches
        ))))


(cl-defmethod corresponding-region ((branch github-link-git-branch)
                                    filename lines)

  (defun chunk-overlaps-region (chunk)
    (let ((selection-first (nth 0 lines))
          (selection-last (nth 1 lines))
          (head-first (plist-get chunk 'head-first))
          (head-last (plist-get chunk 'head-last)))

      (and (<= selection-first head-last)
           (<= head-first selection-last))
    ))

  (let* ((diff-text (github-link-call-git
                     "diff"
                     (format "--unified=%d" github-link-context-lines)
                     (oref branch name)
                     filename))
         (diff-chunks (all-diff-chunk-headers diff-text))
         (has-diff-in-selection (cl-some 'chunk-overlaps-region diff-chunks))
         (selection-first (nth 0 lines))
         (selection-last (nth 1 lines))

         (chunks-before-selection
          (seq-filter (lambda (chunk)
                        (< (plist-get chunk 'head-last) selection-first)
                          )
                      diff-chunks))

         (line-deltas-before-selection
          (mapcar (lambda (chunk) (- (plist-get chunk 'head-length)
                                     (plist-get chunk 'branch-length)))
                  chunks-before-selection))

         (line-offset (seq-reduce #'+ line-deltas-before-selection 0))

         (offset-selection (list (+ selection-first line-offset)
                                 (+ selection-last line-offset)))
         )

    (unless has-diff-in-selection offset-selection)
    ))

(cl-defmethod make-github-link ((branch github-link-git-branch)
                                filename lines)
  (let ((branch-region (corresponding-region branch filename lines)))
    (if branch-region
        (let* ((first-line (nth 0 branch-region))
               (last-line (nth 1 branch-region))
               (line-argument (if (= first-line last-line)
                                  (format "L%d" first-line)
                                (format "L%d-L%d" first-line last-line)))
               (rel-path (string-trim (github-link-call-git "ls-files" filename)))
               (url (string-join
                     (list "https://github.com"
                           (oref branch remote-username) (oref branch remote-repo-name)
                           "blob" (oref branch remote-branch)
                           rel-path
                           )
                     "/"))
               (full-url (concat url "#" line-argument)))
          full-url))))

(defun github-link-get-remote-name (remote-name)
  (let ((remote-url (github-link-call-git "remote" "get-url" remote-name))
        (regex (concat "\\(https?://github.com/\\|git@github.com:\\)"
                       "\\([A-Za-z0-9_-]+\\)"
                       "/"
                       "\\([A-Za-z0-9_-]+\\)"
                       "\\(\\.git\\)?"
                       )))
    (if (string-match regex remote-url)
        (list (match-string 2 remote-url) (match-string 3 remote-url))
        )))


(defun github-link-get-branches ()
  (defun parse-line (line)
    (let* ((line (split-string line "\037"))
           (name (pop line))
           (commit (pop line))
           (remote-full (pop line))
           (remote-full (cond ((not (string-empty-p remote-full)) remote-full)
                              ((string-match-p (regexp-quote "/") name) name)
                              nil))
           (remote-slash-branch
            (if remote-full (split-string remote-full "/")))
           (remote-name (nth 0 remote-slash-branch))
           (remote-branch (nth 1 remote-slash-branch))
           (remote-username-name (if remote-name (github-link-get-remote-name remote-name)))
           (remote-username (nth 0 remote-username-name))
           (remote-repo-name (nth 1 remote-username-name))

           (is-active (string= (pop line) "*")))

      (github-link-git-branch
       :name name
       :commit commit
       :remote-full remote-full
       :remote-name remote-name
       :remote-branch remote-branch
       :remote-username remote-username
       :remote-repo-name remote-repo-name
       :is-active is-active)))

  (let* ((format (string-join '("%(refname:short)"
                                "%(objectname:short)"
                                "%(upstream:short)"
                                "%(HEAD)")
                              "\037"))
         (branch-output (github-link-call-git "branch" "--all"
                                              "--format" format))
         (lines (split-string branch-output "\n" t)))
    (mapcar 'parse-line lines)))


(defun filter-sort (seq key)
  (let* ((decorated (mapcar (lambda (item) (list (funcall key item) item)) seq))
         (filtered (seq-filter 'car decorated))
         (sorted (cl-sort filtered '< :key 'car))
         (undecorated (mapcar (lambda (d) (nth 1 d)) sorted)))
    undecorated))


(defun github-link ()
  (interactive)

  ;; TODO: Prefix argument for explicitly using the current branch only.

  ;; TODO: Double prefix argument for explicitly using the most recent commit.

  (let* ((branches (filter-sort (github-link-get-branches) 'priority))
         (filename (buffer-file-name))
         (region (if (use-region-p) (list (region-beginning) (region-end))
                   (list (point) (point))))
         (lines (mapcar 'line-number-at-pos region))
         (remote-link (cl-some (lambda (branch)
                                 (make-github-link branch filename lines))
                               branches))
         )

    (unless remote-link
      (error "No up-to-date tracking branch found for selection"))


    (message remote-link)
    (kill-new remote-link)
  ))
