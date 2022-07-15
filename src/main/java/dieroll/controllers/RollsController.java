package dieroll.controllers;

import dieroll.models.Roll;
import dieroll.models.RollRequest;
import org.owasp.html.PolicyFactory;
import org.owasp.html.Sanitizers;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.web.bind.annotation.*;

import java.security.SecureRandom;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@RestController
public class RollsController {

    @Autowired
    private SimpMessagingTemplate template;

    @Autowired
    RedisTemplate<String, Roll> redisTemplate;

    private static final SecureRandom RANDOM = new SecureRandom();
    private static final PolicyFactory POLICY_FACTORY = Sanitizers.FORMATTING.and(Sanitizers.LINKS);

    @GetMapping("/rooms/{roomId}/rolls")
    public Set<Roll> getRoomRolls(@PathVariable String roomId) {
        return redisTemplate.opsForZSet().range(roomId, -100, -1);
    }

    @PostMapping(path = "/rolls/{roomId}")
    @ResponseStatus(HttpStatus.CREATED)
    public Roll roll(@DestinationVariable @PathVariable String roomId, @RequestBody RollRequest rollRequest) {
        List<Integer> results = null;
        if (rollRequest.isAValidRoll()) {
            results = rollRequest.getRollingNumbers()
                    .map(numSides -> RANDOM.nextInt(numSides) + 1)
                    .collect(Collectors.toList());
        }
        String sanitizedRequest = POLICY_FACTORY.sanitize(rollRequest.request());
        Roll roll = new Roll(roomId, rollRequest.name(), Instant.now().toEpochMilli(), sanitizedRequest, results);
        persistRollToRedis(roll);
        template.convertAndSend("/topic/rolls/" + roomId, roll);
        return roll;
    }

    private void persistRollToRedis(Roll roll) {
        redisTemplate.opsForZSet().add(roll.roomId(), roll, roll.timestamp());
    }
}
