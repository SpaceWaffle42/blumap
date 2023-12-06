def options():
    while True:
        select = input('''
                    Please select an option to run:
                    [1]Blumap   (Nmap)
                    [2]Blubot   (Discord)
                        
                    [3]Clear Discord
                       Select:''').lower()
        if select == '1' or select == 'blumap':
            import blumap
            break
        if select == '2' or select == 'blubot':
            import blubot
            break
        if select == "3" or select == "clear discord" or select == "clear":
            import channeldelete
            break
        if select == 'exit' or select == "quit":
            break
        else:
            print('Unrecognised command')
if __name__ == "__main__":
    options()