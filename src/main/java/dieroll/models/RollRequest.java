package dieroll.models;

import java.util.Arrays;
import java.util.regex.Pattern;
import java.util.stream.Stream;

public record RollRequest(String name, String request) {

    // Begins with named capture group 'die', consisting of: 'd' followed by 1-60 digits
    // Repeat ',' and the die capture group zero or more times, then end
    private static final Pattern ROLL_PATTERN = Pattern.compile("^(?<die>d\\d{1,60})(,\\k<die>)*$");

    public Stream<Integer> getRollingNumbers() {
        return Arrays.stream(request.replace("d", "").split(",")).map(Integer::valueOf);
    }

    public boolean isAValidRoll() {
        return ROLL_PATTERN.matcher(request).matches();
    }

}
