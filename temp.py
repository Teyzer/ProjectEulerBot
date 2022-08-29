if __name__ == "__main__":

    s = [1/i for i in range(2007, 2022+1)]

    m = pow(2, len(s))

    minimum_obtained = sum(s)
    configuration = ""

    for b in range(m):

        choices = str(bin(b))[2::]
        choices = choices + "0" * (len(s) - len(choices))

        first_sum = 0
        second_sum = 0

        for index, char in enumerate(choices):
            if char == "1":
                first_sum += s[index]
            else:
                second_sum += s[index]

        difference = abs(first_sum - second_sum)

        if choices == "1001011001101001":
            print(difference)

        if difference < minimum_obtained:
            minimum_obtained = difference
            configuration = choices

    print(configuration, minimum_obtained)
