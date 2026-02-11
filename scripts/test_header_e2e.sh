#!/bin/bash
source $HOME/.nvm/nvm.sh
nvm use 22
cd apps/studio
npx playwright test e2e/tests/02-header/header.spec.js
