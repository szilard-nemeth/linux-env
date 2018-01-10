set backspace=indent,eol,start

" Turn on line numbers
set number

" Search while typing pattern
set incsearch

" Highlight search pattern matches
set hlsearch

" Draw a margin in the 121 column
set colorcolumn=121

" Show current line and column numbers
set ruler

" Command line is 2 lines, so it's easier to type complex commands
set cmdheight=2

" Highlight syntax
syntax on
syntax enable
colorscheme darcula

" Some nice colorscheme
colors evening

" Make constants readable on projector as well
highlight Constant ctermbg=black ctermfg=green

" Always highlight tabs and trailing spaces.
set list
set listchars=tab:>\ ,trail:.,nbsp:.

" Always assume Unix-style line endings
set fileformats=unix
