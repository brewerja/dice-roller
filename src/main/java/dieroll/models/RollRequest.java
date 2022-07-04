package dieroll.models;

import java.util.Arrays;
import java.util.stream.Collectors;

public record RollRequest(String name, String request) {

    public String getRequestDisplay() {
        return Arrays.stream(request.split(",")).map(r -> "d" + r).collect(Collectors.joining(","));
    }

}
