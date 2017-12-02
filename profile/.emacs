(setq inhibit-splash-screen t)

(global-set-key "\C-h" 'backward-delete-char)

(global-set-key "\C-cw" 'compare-windows)
(global-set-key "\C-xp" 'other-window)
(global-set-key "\M- " 'set-mark-command)
(global-set-key "\M-r" 'query-replace-regexp)
(global-set-key "\C-xg" 'goto-line)
(global-set-key [home] 'beginning-of-line)
(global-set-key [end] 'end-of-line)

;; Change the binding of mouse button 2, so that it inserts the
;; selection at point (where the text cursor is), instead of at
;; the position clicked.
;;
(define-key global-map [button2] 'x-insert-selection)

(setq-default indent-tabs-mode nil)
(setq-default tab-width 4)
(setq-default py-indent-offset 4)
(setq-default python-indent 4)
(setq tab-width 4)
(setq c-site-default-style "bsd")
(setq c-recognize-knr-p nil)

;; This controls indentation.  The default is 4 spaces but the
;; Emacs source code uses 2.
(setq c-basic-offset 4)

(global-font-lock-mode t)
(require 'font-lock)
(set-face-foreground 'font-lock-string-face "forest green")

(setq emacs-version "XEmacs")


;;; ********************
;;; Font-Lock is a syntax-highlighting package.  When it is enabled and you
;;; are editing a program, different parts of your program will appear in
;;; different fonts or colors.  For example, with the code below, comments
;;; appear in red italics, function names in function definitions appear in
;;; blue bold, etc.  The code below will cause font-lock to automatically be
;;; enabled when you edit C, C++, Emacs-Lisp, and many other kinds of
;;; programs.
;;;
;;; The "Options" menu has some commands for controlling this as well.
;;;
(cond ((string-match "XEmacs\\|Lucid" emacs-version)
       (require 'font-lock)
       (set-face-foreground 'font-lock-function-name-face "blue")
       (set-face-foreground 'font-lock-comment-face "brown")
       (set-face-underline-p 'font-lock-string-face nil)
       (make-face-unitalic 'font-lock-string-face)
       (make-face-unitalic 'font-lock-function-name-face)
       (add-hook 'emacs-lisp-mode-hook	'turn-on-font-lock)
       (add-hook 'lisp-mode-hook	'turn-on-font-lock)
       (add-hook 'c-mode-hook		'turn-on-font-lock)
       (add-hook 'c++-mode-hook		'turn-on-font-lock)
       (add-hook 'perl-mode-hook	'turn-on-font-lock)
       (add-hook 'tex-mode-hook		'turn-on-font-lock)
       (add-hook 'texinfo-mode-hook	'turn-on-font-lock)
       (add-hook 'postscript-mode-hook	'turn-on-font-lock)
       (add-hook 'dired-mode-hook	'turn-on-font-lock)
       (add-hook 'ada-mode-hook		'turn-on-font-lock)
       ))

;;; fast-lock is a package which speeds up the highlighting of files
;;; by saving information about a font-locked buffer to a file and
;;; loading that information when the file is loaded again.  This
;;; requires a little extra disk space be used.
;;;
;;; Normally fast-lock puts the cache file (the filename appended with
;;; .flc) in the same directory as the file it caches.  You can
;;; specify an alternate directory to use by setting the variable
;;; fast-lock-cache-directories.

;(add-hook 'font-lock-mode-hook 'turn-on-fast-lock)
;(setq fast-lock-cache-directories '("/foo/bar/baz"))
(custom-set-variables
  ;; custom-set-variables was added by Custom.
  ;; If you edit it by hand, you could mess it up, so be careful.
  ;; Your init file should contain only one such instance.
  ;; If there is more than one, they won't work right.
 '(case-fold-search t)
 '(current-language-environment "English")
 '(global-font-lock-mode t nil (font-lock))
 '(org-startup-truncated nil)
 '(ps-printer-name-option "-PPostscript")
 '(tool-bar-mode nil))
(custom-set-faces
  ;; custom-set-faces was added by Custom.
  ;; If you edit it by hand, you could mess it up, so be careful.
  ;; Your init file should contain only one such instance.
  ;; If there is more than one, they won't work right.
 '(default ((t (:inherit nil :stipple nil :background "white" :foreground "black" :inverse-video nil :box nil :strike-through nil :overline nil :underline nil :slant normal :weight normal :height 90 :width normal :foundry "unknown" :family "DejaVu Sans Mono")))))

; allow remote editing over scp
(require 'tramp)
(setq tramp-default-method "scp")
