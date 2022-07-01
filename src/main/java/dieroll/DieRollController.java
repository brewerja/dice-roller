package dieroll;

import dieroll.models.DieRoll;
import dieroll.models.DieRollRequest;
import dieroll.models.Message;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.stereotype.Controller;

import java.util.Arrays;
import java.util.Random;
import java.util.stream.Collectors;

@Controller
public class DieRollController {

    private static final Random RANDOM = new Random();

    @MessageMapping("/roll")
    @SendTo("/topic/rolls")
    public DieRoll roll(DieRollRequest dieRollRequest) throws Exception {
        String result = Arrays.stream(dieRollRequest.request().split(","))
                .map(numSides -> RANDOM.nextInt(Integer.parseInt(numSides)) + 1)
                .map(Object::toString)
                .collect(Collectors.joining(","));
        return new DieRoll(dieRollRequest.name(), dieRollRequest.request(), result);
    }

    @MessageMapping("/message")
    @SendTo("/topic/messages")
    public Message talk(Message message) {
        return message;
    }

}
