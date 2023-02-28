#!/usr/bin/env bash

function brewinstall {
	HOMEBREW_NO_AUTO_UPDATE=1 brew install $1
}