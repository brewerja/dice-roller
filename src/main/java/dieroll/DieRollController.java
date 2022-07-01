package dieroll;

import java.util.Random;

import dieroll.models.DieRoll;
import dieroll.models.DieRollRequest;
import dieroll.models.Message;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.stereotype.Controller;

@Controller
public class DieRollController {

    private static final Random RANDOM = new Random();

    @MessageMapping("/roll")
    @SendTo("/topic/rolls")
    public DieRoll roll(DieRollRequest dieRollRequest) throws Exception {
        Integer result = RANDOM.nextInt(dieRollRequest.numSides()) + 1;
        return new DieRoll(dieRollRequest.name(), dieRollRequest.numSides(), result);
    }

    @MessageMapping("/message")
    @SendTo("/topic/messages")
    public Message talk(Message message) {
        return message;
    }

}
