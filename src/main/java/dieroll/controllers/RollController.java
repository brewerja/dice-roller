package dieroll.controllers;

import dieroll.models.Roll;
import dieroll.models.RollRequest;
import org.owasp.html.PolicyFactory;
import org.owasp.html.Sanitizers;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.ModelAndView;

import java.security.SecureRandom;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@RestController
public class RollController {

    private static final SecureRandom RANDOM = new SecureRandom();
    private static final PolicyFactory POLICY_FACTORY = Sanitizers.FORMATTING.and(Sanitizers.LINKS);

    @Autowired
    RedisTemplate<String, Roll> redisTemplate;

    @GetMapping("/rooms/{roomId}")
    public ModelAndView rooms(@PathVariable String roomId, Model model) {
        model.addAttribute("roomId", roomId);
        return new ModelAndView("room");
    }

    @GetMapping(path = "/rooms/{roomId}/rolls")
    public Set<Roll> getRoomRolls(@PathVariable String roomId) {
        return redisTemplate.opsForZSet().range(roomId, -100, -1);
    }

    @MessageMapping("/roll/{roomId}")
    @SendTo("/topic/rolls/{roomId}")
    public Roll roll(@DestinationVariable String roomId, RollRequest rollRequest) {
        List<Integer> results = null;
        if (rollRequest.isAValidRoll()) {
            results = rollRequest.getRollingNumbers()
                    .map(numSides -> RANDOM.nextInt(numSides) + 1)
                    .collect(Collectors.toList());
        }
        String sanitizedRequest = POLICY_FACTORY.sanitize(rollRequest.request());
        Roll roll = new Roll(roomId, rollRequest.name(), Instant.now().toEpochMilli(), sanitizedRequest, results);
        persistRollToRedis(roll);
        return roll;
    }

    private void persistRollToRedis(Roll roll) {
        redisTemplate.opsForZSet().add(roll.roomId(), roll, roll.timestamp());
    }

}
