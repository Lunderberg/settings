#!/usr/bin/env python3

import os
import subprocess

users = ['eric', 'octo']

def main():
    current_user = os.environ['USER']
    current_user_index = users.index(current_user)
    next_user_index = (current_user_index + 1) % len(users)
    next_user = users[next_user_index]
    subprocess.check_call(['dm-tool', 'switch-to-user', next_user])

if __name__ == '__main__':
    main()
