#TODO add warning about overwrite before copying to home directory!

yes | cp -aR ./aliases/. ~/aliases/
yes | cp -aR ./dotfiles/. ~/
cp .bashrc ~/.bashrc;

source ~/.bashrc
