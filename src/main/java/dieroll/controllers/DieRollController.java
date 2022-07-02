package dieroll.controllers;

import dieroll.models.DieRoll;
import dieroll.models.DieRollRequest;
import dieroll.models.Message;
import org.springframework.http.HttpStatus;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.stereotype.Controller;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.Arrays;
import java.util.Random;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Controller
public class DieRollController {

    private static final Random RANDOM = new Random();
    private static final Pattern ROLL_PATTERN = Pattern.compile("^[\\d,]{1,60}$");

    @MessageMapping("/roll")
    @SendTo("/topic/rolls")
    public DieRoll roll(DieRollRequest dieRollRequest) {
        if (!ROLL_PATTERN.matcher(dieRollRequest.request()).matches())
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Bad roll string");
        String result = Arrays.stream(dieRollRequest.request().split(","))
                .filter(s -> !s.isEmpty())
                .map(numSides -> RANDOM.nextInt(Integer.parseInt(numSides)) + 1)
                .map(Object::toString)
                .collect(Collectors.joining(","));
        return new DieRoll(dieRollRequest.name(), Instant.now().toEpochMilli(), dieRollRequest.request(), result);
    }

    @MessageMapping("/message")
    @SendTo("/topic/messages")
    public Message talk(Message message) {
        return message;
    }

}
