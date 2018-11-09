import credentials
import login_dialog

cred = credentials._get_credentials()

if 'username' in cred and 'apiKey' in cred:
    validation = credentials._check_credentials(
        cred['username'],
        cred['apiKey']
    )
    if validation is False:
        login_dialog.run_login()

else:
    login_dialog.run_login()
