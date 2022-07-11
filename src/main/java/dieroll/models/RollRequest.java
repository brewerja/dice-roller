package dieroll.models;

import java.util.Arrays;
import java.util.stream.Collectors;

public record RollRequest(String name, String request) {

    public String getRequestDisplay() {
        if (request.charAt(0) == '#')
            return Arrays.stream(request.substring(1).split(",")).map(r -> "d" + r).collect(Collectors.joining(","));
        else
            return request;
    }

}
