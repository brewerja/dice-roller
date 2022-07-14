package dieroll.models;

import java.util.Arrays;
import java.util.regex.Pattern;
import java.util.stream.Stream;

public record RollRequest(String name, String request) {

    // Begin with 'd' followed by 1-10 digits
    // Repeat ',' and the same pattern as above 0-9 times, then end
    private static final Pattern ROLL_PATTERN = Pattern.compile("^d\\d{1,10}(?:,d\\d{1,10}){0,9}$");

    public Stream<Integer> getRollingNumbers() {
        return Arrays.stream(request.replace("d", "").split(",")).map(Integer::valueOf);
    }

    public boolean isAValidRoll() {
        return ROLL_PATTERN.matcher(request).matches();
    }

}
