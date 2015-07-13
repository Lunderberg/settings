;Adapted from "go--apply-rcs-patch" from go-mode.el
;; Copyright 2013 The Go Authors. All rights reserved.
;; Use of this source code is governed by a BSD-style
;; license that can be found in the LICENSE file.

;; Copyright (c) 2012 The Go Authors. All rights reserved.

;; Redistribution and use in source and binary forms, with or without
;; modification, are permitted provided that the following conditions are
;; met:

;;    * Redistributions of source code must retain the above copyright
;; notice, this list of conditions and the following disclaimer.
;;    * Redistributions in binary form must reproduce the above
;; copyright notice, this list of conditions and the following disclaimer
;; in the documentation and/or other materials provided with the
;; distribution.
;;    * Neither the name of Google Inc. nor the names of its
;; contributors may be used to endorse or promote products derived from
;; this software without specific prior written permission.

;; THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
;; "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
;; LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
;; A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
;; OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
;; SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
;; LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
;; DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
;; THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
;; (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
;; OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


;;Apply an rcs patch to the current buffer.
(defun apply-rcs-patch (patch-buffer)
	"Apply an RCS-formatted diff from PATCH-BUFFER to the current
   	buffer."
	(let ((target-buffer (current-buffer))
				;; Relative offset between buffer line numbers and line numbers
				;; in patch.
				;;
				;; Line numbers in the patch are based on the source file, so
				;; we have to keep an offset when making changes to the
				;; buffer.
				;;
				;; Appending lines decrements the offset (possibly making it
				;; negative), deleting lines increments it. This order
				;; simplifies the forward-line invocations.
				(line-offset 0))
		(save-excursion
			(with-current-buffer patch-buffer
				(goto-char (point-min))
				(while (not (eobp))
					(unless (looking-at "^\\([ad]\\)\\([0-9]+\\) \\([0-9]+\\)")
						(error "invalid rcs patch or internal error in go--apply-rcs-patch"))
					(forward-line)
					(let ((action (match-string 1))
								(from (string-to-number (match-string 2)))
								(len  (string-to-number (match-string 3))))
						(cond
						 ((equal action "a")
							(let ((start (point)))
								(forward-line len)
								(let ((text (buffer-substring start (point))))
									(with-current-buffer target-buffer
										(decf line-offset len)
										(goto-char (point-min))
										(forward-line (- from len line-offset))
										(insert text)))))
						 ((equal action "d")
							(with-current-buffer target-buffer
								(goto-char (point-min))
								(forward-line (1- (- from line-offset)))
								(incf line-offset len)
								(let ((start (point)))
									(forward-line len)
									(delete-region start (point)))))
						 (t
							(error "invalid rcs patch or internal error in apply-rcs-patch")))))))))