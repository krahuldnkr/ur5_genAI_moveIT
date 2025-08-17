from parser.parser import parse_command

if __name__ == "__main__":
    user_input = input("Enter command: ")
    result = parse_command(user_input)
    print(result)
